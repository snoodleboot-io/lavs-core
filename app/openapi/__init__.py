"""OpenAPI release polish for the LAVS API.

Holds the application's static metadata (title, description, installed
version) and the customizer that injects the deployment's real security
schemes into the generated OpenAPI document. Public symbols are imported
directly from their defining modules (e.g. ``app.openapi.app_metadata``);
this package does not re-export them.
"""
