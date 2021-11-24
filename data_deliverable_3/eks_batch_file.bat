cd "C:\Users\My_User\Documents\Wizeline_data\data_deliverable_1" 
terraform init
terraform apply --var-file=terraform.tfvars
terraform apply --var-file=terraform.tfvars
aws eks --region us-east-2 update-kubeconfig --name airflow-eks-data-bootcamp
kubectl create namespace storage
for /f %%i in ('terraform output efs') do helm install nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner --namespace storage --set nfs.server=%%i --set nfs.path=/
kubectl create namespace airflow
helm install airflow -f airflow-values.yaml apache-airflow/airflow --namespace airflow
eksctl create iamidentitymapping --cluster airflow-eks-data-bootcamp --namespace airflow --service-name "emr-containers"
eksctl utils associate-iam-oidc-provider --cluster airflow-eks-data-bootcamp --approve
aws emr-containers update-role-trust-policy --cluster-name airflow-eks-data-bootcamp --namespace airflow --role-name EMRContainers-JobExecutionRole
aws emr-containers create-virtual-cluster --name virtual_cluster_test --container-provider "{ ""id"": ""airflow-eks-data-bootcamp"", ""type"": ""EKS"", ""info"": { ""eksInfo"": { ""namespace"": ""airflow"" } } }"
pause