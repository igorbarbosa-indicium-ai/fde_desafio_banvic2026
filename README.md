# Template ELT Banvic

Template de repositório para ingestão ELT de arquivos CSV locais em PostgreSQL, com Meltano, Airflow, Docker Compose, Kind, Terraform e GitHub Actions.

Depois de publicar este projeto no GitHub, habilite **Settings > General > Template repository** para permitir que outros repositórios sejam criados a partir dele.

## Arquitetura

- O sensor do Airflow verifica diariamente a pasta de entrada e aguarda até 24 horas por um `.zip` novo.
- Uma tarefa Python extrai os CSVs com validação contra path traversal. Após a carga bem-sucedida, o ZIP é movido para `processed/`.
- Meltano executa `tap-csv` e `target-postgres`; cada CSV encontrado vira uma tabela com o nome do arquivo.
- PostgreSQL hospeda o data warehouse e o metadatabase do Airflow em bancos separados.
- Docker Compose oferece o ambiente local. Para Kubernetes, Kind executa o cluster local em containers Docker; Terraform gerencia os namespaces e o workload Airflow.
- Terraform cria um namespace Kubernetes por ambiente (`banvic-dev`, `banvic-hom`, `banvic-prod`), além de um Deployment Airflow com duas réplicas e um Service `LoadBalancer`.
- GitHub Actions valida Terraform e os testes Python em pull requests. O apply é manual e executado por runner self-hosted conectado ao cluster Kind do Docker Desktop.

## Pré-requisitos

- Docker Desktop com Docker Compose v2
- Python 3.12+
- Terraform 1.9+
- Kind, kubectl e Go para o fluxo Kubernetes e o controlador LoadBalancer do Kind
- GitHub Actions habilitado e um runner self-hosted com acesso ao cluster para deploy

## Desenvolvimento local

```bash
mkdir -p incoming
docker compose up --build -d
```

A interface do Airflow fica em `http://localhost:8080`. O comando `standalone` cria um usuário administrativo local e imprime as credenciais nos logs; obtenha-as com `docker compose logs airflow`.

Coloque os arquivos `.zip` recebidos em `incoming/`. O sensor `wait_for_archive` os verifica de hora em hora dentro da janela diária. A pasta também contém `extracted/` e `processed/`, criadas durante a execução. Para apontar para outra pasta on-premises, ajuste `SOURCE_DIR` no `.env`.

Para executar Meltano manualmente:

```bash
docker compose --profile tools run --rm meltano meltano run tap-csv target-postgres
```

Os CSVs de demonstração em `data-src/banvic_data2026/` estão configurados em `meltano.yml`. Para os arquivos dinâmicos dos ZIPs, o DAG passa a configuração `TAP_CSV_FILES` ao Meltano.

## Docker Desktop e Kind

Docker Compose e Kubernetes são fluxos de execução distintos. Crie um cluster Kind de um nó usando o Docker Engine do Docker Desktop e monte a pasta de entrada no nó:

```bash
mkdir -p incoming
sed "s|__INCOMING_PATH__|$(realpath incoming)|" infra/kubernetes/kind-config.yaml > /tmp/banvic-kind-config.yaml
kind create cluster --name banvic --config /tmp/banvic-kind-config.yaml
docker build -t banvic-elt:dev -f docker/airflow/Dockerfile .
kind load docker-image banvic-elt:dev --name banvic
```

O Service `LoadBalancer` do Kubernetes precisa de um controlador externo no Kind. Instale Cloud Provider Kind com Go e mantenha-o em execução em um terminal separado:

```bash
go install sigs.k8s.io/cloud-provider-kind@latest
kubectl label node kind-banvic-control-plane node.kubernetes.io/exclude-from-external-load-balancers-
"$(go env GOPATH)/bin/cloud-provider-kind" --enable-lb-port-mapping
```

Crie no namespace desejado o Secret `banvic-airflow-runtime` antes do apply. Ele deve fornecer as variáveis de runtime do Airflow, incluindo `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` apontando para um PostgreSQL acessível pelo cluster, `TARGET_POSTGRES_HOST`, `TARGET_POSTGRES_PORT`, `TARGET_POSTGRES_USER`, `TARGET_POSTGRES_PASSWORD` e `TARGET_POSTGRES_DATABASE`. Não use SQLite para duas réplicas nem armazene credenciais nos arquivos Terraform.

O Terraform cria as duas réplicas do Airflow e o Service que distribui requisições entre os pods:

```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform apply -var-file=environments/dev.tfvars
kubectl get pods,services -n banvic-dev
kubectl get service banvic-airflow -n banvic-dev --watch
```

Confira o `EXTERNAL-IP` com `kubectl get service banvic-airflow -n banvic-dev` e a porta do host mapeada pelo controlador com `docker ps --filter "name=kindccm"`. Acesse `http://<EXTERNAL-IP>:8080`. A configuração usa `hostPath` para montar `incoming/` dentro do nó; esse diretório deve existir antes de criar o cluster. O banco PostgreSQL não é criado pelo Terraform e deve ser provisionado separadamente. Para remover o cluster local:

```bash
kind delete cluster --name banvic
```

Não inclua credenciais nos arquivos versionados. O Airflow em múltiplas réplicas requer PostgreSQL compartilhado e acessível a todos os pods.

## Terraform e GitHub Actions

Os arquivos `infra/terraform/environments/{dev,hom,prod}.tfvars` selecionam o namespace-alvo. Valide localmente com:

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -var-file=environments/dev.tfvars
```

O workflow `Terraform validation` roda em pull requests. O workflow `Terraform deploy` é acionado manualmente em **Actions > Terraform deploy**, aceita `dev`, `hom` ou `prod` e exige um runner self-hosted Linux com labels `docker-desktop` e `kind`, Docker Desktop ativo, Cloud Provider Kind em execução, contexto `kind-banvic`, imagem carregada e Secret criado no namespace selecionado. Configure também ambientes de proteção no GitHub, especialmente para `prod`.

Antes de uso colaborativo ou produção, configure um backend remoto de estado Terraform compartilhado e protegido, e inclua os módulos do provedor escolhido. O workflow de deploy usa o backend configurado pelo projeto; o estado local padrão não é adequado para runners efêmeros ou execução concorrente.

## Testes

```bash
python -m unittest discover -s tests -v
docker compose --env-file .env config --quiet
```

Os testes cobrem extração normal e rejeição de caminhos ZIP que escapariam do diretório de destino.

## Estrutura

```text
app/                 Extração segura dos ZIPs
dags/                Sensor e pipeline ELT diário
data-src/            CSVs de demonstração
docker/              Imagem Airflow e inicialização do PostgreSQL
infra/terraform/     Namespaces dev, hom e prod
infra/kubernetes/   Configuração do cluster Kind
.github/workflows/   Validação e deploy Terraform
```
