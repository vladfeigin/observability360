locals {
  aks_subnet_name = "akssubnet"
}

resource "azurerm_virtual_network" "demo" {
  name                = "${var.base_name}-vnet"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  address_space       = [var.virtual_network_address_prefix]

}

# AKS Subnet
resource "azurerm_subnet" "aks" {
  name                 = local.aks_subnet_name
  resource_group_name  = azurerm_resource_group.demo.name
  virtual_network_name = azurerm_virtual_network.demo.name
  address_prefixes     = [var.aks_subnet_address_prefix]
}

resource "azurerm_network_security_group" "aks" {
  name                = "${var.base_name}-aks-nsg"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
}

resource "azurerm_network_security_rule" "aks_http" {
  name                        = "${var.base_name}-http-rule"
  resource_group_name         = azurerm_resource_group.demo.name
  network_security_group_name = azurerm_network_security_group.aks.name
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "80"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}
