param location string
param environmentName string
param uniqueSuffix string
param tags object

// Storage Account
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${uniqueSuffix}' // uniqueSuffix is already 13 chars, total = 15 (within 3-24 limit)
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: true
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// Azure AI Search
resource aiSearch 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: 'srch-${environmentName}-${uniqueSuffix}'
  location: location
  tags: tags
  sku: {
    name: 'standard'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'enabled'
    disableLocalAuth: false // Enable both Key Auth and Managed Identity
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
  }
}

// Azure AI Foundry (Cognitive Services account with AIServices kind)
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: 'ai-${environmentName}-${uniqueSuffix}'
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: 'ai-${environmentName}-${uniqueSuffix}'
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
    disableLocalAuth: false // Enable both Key Auth and Managed Identity
    allowProjectManagement: true
  }
}

// Deploy gpt-4o-mini model
resource gpt4oMiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: aiFoundry
  name: 'gpt-4o-mini'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

// RBAC Assignments - Grant AI Foundry access to Storage
// Storage Blob Data Contributor role
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, aiFoundry.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storage
  properties: {
    principalId: aiFoundry.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Storage Table Data Contributor role
resource storageTableRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, aiFoundry.id, '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
  scope: storage
  properties: {
    principalId: aiFoundry.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3') // Storage Table Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Storage Queue Data Contributor role
resource storageQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, aiFoundry.id, '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
  scope: storage
  properties: {
    principalId: aiFoundry.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88') // Storage Queue Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Grant AI Foundry access to AI Search
// Search Index Data Contributor role
resource searchIndexRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiSearch.id, aiFoundry.id, '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
  scope: aiSearch
  properties: {
    principalId: aiFoundry.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7') // Search Index Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Search Service Contributor role
resource searchServiceRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiSearch.id, aiFoundry.id, '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
  scope: aiSearch
  properties: {
    principalId: aiFoundry.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0') // Search Service Contributor
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output storageName string = storage.name
output storageEndpoint string = storage.properties.primaryEndpoints.blob
output aiSearchName string = aiSearch.name
output aiSearchEndpoint string = 'https://${aiSearch.name}.search.windows.net'
output aiFoundryName string = aiFoundry.name
output aiFoundryEndpoint string = aiFoundry.properties.endpoint
output aiFoundryPrincipalId string = aiFoundry.identity.principalId
output gpt4oMiniDeploymentName string = gpt4oMiniDeployment.name
