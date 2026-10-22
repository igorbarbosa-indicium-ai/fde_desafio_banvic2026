# Rancher

O Compose é a configuração-base dos serviços de desenvolvimento. Use Kompose para gerar os manifests e revise-os antes de aplicar no Rancher, conforme o procedimento do README raiz.

Esta pasta não armazena manifests gerados nem credenciais. Gere-os em `generated/` localmente, valide secrets, volumes, `imagePullPolicy` e persistência do PostgreSQL, e só então aplique no namespace criado pelo Terraform.