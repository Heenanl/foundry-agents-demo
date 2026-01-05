targetScope = 'subscription'

@description('Name of the environment')
param environmentName string

@description('Primary location for all resources')
@allowed([ 'uaenorth', 'southafricanorth', 'westeurope', 'southcentralus', 'australiaeast', 'canadaeast', 'eastus', 'eastus2', 'francecentral', 'japaneast', 'northcentralus', 'swedencentral', 'switzerlandnorth', 'uksouth' ])
param location string

@description('Tags to be applied to all resources')
param tags object = {
  'azd-env-name': environmentName
  Environment: environmentName
}

// Generate a unique string for resource naming
var uniqueSuffix = uniqueString(subscription().id, environmentName, location)
var resourceGroupName = 'rg-${environmentName}-${uniqueSuffix}'

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Deploy main resources
module resources 'resources.bicep' = {
  name: 'resources-deployment'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    uniqueSuffix: uniqueSuffix
    tags: tags
  }
}

// Outputs
output resourceGroupName string = rg.name
output aiFoundryName string = resources.outputs.aiFoundryName
output aiFoundryEndpoint string = resources.outputs.aiFoundryEndpoint
output storageName string = resources.outputs.storageName
output aiSearchName string = resources.outputs.aiSearchName
output aiSearchEndpoint string = resources.outputs.aiSearchEndpoint
output aiFoundryPrincipalId string = resources.outputs.aiFoundryPrincipalId
