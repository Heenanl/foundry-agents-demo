using './main.bicep'

// ============================================================================
// BASIC PARAMETERS
// ============================================================================
param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'dev')
param location = readEnvironmentVariable('AZURE_LOCATION', 'swedencentral')
