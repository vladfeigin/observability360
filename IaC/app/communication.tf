resource "azurerm_communication_service" "demo" {
  name                = "${var.base_name}-communicationservice"
  resource_group_name = data.azurerm_resource_group.demo.name
  data_location       = var.data_location
}

resource "azurerm_email_communication_service" "demo" {
  name                = "${var.base_name}-emailcommunicationservice"
  resource_group_name = data.azurerm_resource_group.demo.name
  data_location       = var.data_location
}

resource "azurerm_email_communication_service_domain" "demo" {
  name             = "AzureManagedDomain"
  email_service_id = azurerm_email_communication_service.demo.id

  domain_management = "AzureManaged"
}

resource "azurerm_communication_service_email_domain_association" "demo" {
  communication_service_id = azurerm_communication_service.demo.id
  email_service_domain_id  = azurerm_email_communication_service_domain.demo.id
}

resource "azurerm_role_definition" "communication_service_role" {
  name        = "${var.base_name}-ACS_Email_Write"
  scope       = azurerm_communication_service.demo.id
  description = "Allows for full access to the Azure Communication Service resource, including the ability to manage data and settings."
  permissions {
    actions = [
      "*/read",
      "Microsoft.Communication/CommunicationServices/Read",
      "Microsoft.Communication/CommunicationServices/Write",
      "Microsoft.Communication/EmailServices/write"
    ]
  }
}