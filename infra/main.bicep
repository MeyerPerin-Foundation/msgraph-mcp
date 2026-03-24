@description('Name of the Web App')
param appName string = 'msgraph-mcp'

@description('Location for the Web App (must match the App Service Plan)')
param location string = 'Canada Central'

@description('Resource ID of the existing App Service Plan')
param appServicePlanId string = '/subscriptions/333a3e2f-80b1-452b-8691-bcfdc67987ad/resourceGroups/research/providers/Microsoft.Web/serverfarms/ASP-research'

@description('Python version')
param pythonVersion string = '3.13'

resource webApp 'Microsoft.Web/sites@2024-04-01' = {
  name: appName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlanId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|${pythonVersion}'
      appCommandLine: 'gunicorn msgraph_mcp.server:app -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 --forwarded-allow-ips="*"'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
      ]
    }
  }
}

output webAppName string = webApp.name
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
