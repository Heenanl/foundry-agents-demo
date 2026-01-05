Run with:

```
# append --tenant-id <your-tenant-id> if needed
# append --use-device-code if needed
azd auth login 

# make sure you're in the folder with the azure.yaml file
azd env new "andreea-foundry" --location "eastus"
# this should create an .azure folder with the environment configuration

# run the deployment
azd up
```