# Template ELT Banvic

Template de repositório para ingestão ELT de arquivos CSV locais em PostgreSQL, com Meltano, Airflow, Docker Compose, Minikube, Terraform e GitHub Actions.

Depois de publicar este projeto no GitHub, habilite **Settings > General > Template repository** para permitir que outros repositórios sejam criados a partir dele.

## Arquitetura

- O sensor do Airflow verifica diariamente a pasta de entrada e aguarda até 24 horas por um `.zip` novo.
- Uma tarefa Python extrai os CSVs com validação contra path traversal. Após a carga bem-sucedida, o ZIP é movido para `processed/`.
- Meltano executa `tap-csv` e `target-postgres`; cada CSV encontrado vira uma tabela com o nome do arquivo.
- PostgreSQL hospeda o data warehouse e o metadatabase do Airflow em bancos separados.
- Docker Compose oferece o ambiente local. Para Kubernetes, converta e revise os serviços com Kompose antes de aplicá-los no Minikube.
- Terraform cria um namespace Kubernetes por ambiente (`banvic-dev`, `banvic-hom`, `banvic-prod`). O módulo é uma base: rede, cluster, armazenamento e serviços gerenciados dependem do provedor de nuvem escolhido.
- GitHub Actions valida Terraform e os testes Python em pull requests. O apply é manual e executado por runner self-hosted conectado ao Minikube.

## Pré-requisitos

- Docker Desktop com Docker Compose v2
- Python 3.12+
- Terraform 1.9+
- Minikube, kubectl e Kompose para o fluxo Kubernetes
- GitHub Actions habilitado e um runner self-hosted com acesso ao cluster para deploy

## Desenvolvimento local

```powershell
New-Item -ItemType Directory -Force incoming
docker compose up --build -d
```

A interface do Airflow fica em `http://localhost:8080`. O comando `standalone` cria um usuário administrativo local e imprime as credenciais nos logs; obtenha-as com `docker compose logs airflow`.

Coloque os arquivos `.zip` recebidos em `incoming/`. O sensor `wait_for_archive` os verifica de hora em hora dentro da janela diária. A pasta também contém `extracted/` e `processed/`, criadas durante a execução. Para apontar para outra pasta on-premises, ajuste `SOURCE_DIR` no `.env`.

Para executar Meltano manualmente:

```powershell
docker compose --profile tools run --rm meltano meltano run tap-csv target-postgres
```

Os CSVs de demonstração em `data-src/banvic_data2026/` estão configurados em `meltano.yml`. Para os arquivos dinâmicos dos ZIPs, o DAG passa a configuração `TAP_CSV_FILES` ao Meltano.

## Rancher

Compose e Kubernetes são fluxos de execução distintos. Para gerar manifests Kubernetes a partir dos serviços locais:

```powershell
rdctl start --kubernetes.enabled=true --container-engine.name=docker
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform apply -var-file=environments/dev.tfvars
kubectl image build -t banvic-elt:dev -f docker/airflow/Dockerfile .
kompose convert -f docker-compose.yml -o infra/kubernetes/generated
```

Revise os manifests antes de aplicar: configure os Secrets do Kubernetes em vez de embutir o `.env`, defina `imagePullPolicy: IfNotPresent` para a imagem local, e ajuste os volumes para o diretório on-premises. O caminho do host precisa estar montado no nó Minikube (por exemplo, com `rancher-desktop mount`) e representado por um `hostPath` apropriado. Só então aplique os manifests no namespace Terraform:

```powershell
kubectl apply -n banvic-dev -f infra/kubernetes/generated
```

Não aplique os manifests gerados sem revisar credenciais, volumes, portas e armazenamento persistente.

## Terraform e GitHub Actions

Os arquivos `infra/terraform/environments/{dev,hom,prod}.tfvars` selecionam o namespace-alvo. Valide localmente com:

```powershell
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -var-file=environments/dev.tfvars
```

O workflow `Terraform validation` roda em pull requests. O workflow `Terraform deploy` é acionado manualmente em **Actions > Terraform deploy**, aceita `dev`, `hom` ou `prod` e exige um runner self-hosted com label `rancher-desktop` e kubeconfig autorizado. Configure também ambientes de proteção no GitHub, especialmente para `prod`.

Antes de uso colaborativo ou produção, configure um backend remoto de estado Terraform compartilhado e protegido, e inclua os módulos do provedor escolhido. O workflow de deploy usa o backend configurado pelo projeto; o estado local padrão não é adequado para runners efêmeros ou execução concorrente.

## Testes

```powershell
python -m unittest discover -s tests -v
docker compose --env-file .env.example config --quiet
```

Os testes cobrem extração normal e rejeição de caminhos ZIP que escapariam do diretório de destino.

## Estrutura

```text
app/                 Extração segura dos ZIPs
dags/                Sensor e pipeline ELT diário
data-src/            CSVs de demonstração
docker/              Imagem Airflow e inicialização do PostgreSQL
infra/terraform/     Namespaces dev, hom e prod
.github/workflows/   Validação e deploy Terraform
```
