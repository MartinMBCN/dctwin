Sprint 6 – Production Deployment

Goal

Deploy the Digital Career Twin as a secure, publicly accessible web application running in Azure, with automated deployment, custom domain, HTTPS, and operational monitoring.

Objectives

Deploy backend and frontend to Azure.
Configure production environment variables and secrets.
Connect www.digitalcareertwin.ai.
Enable managed HTTPS certificates.
Configure automated deployment from GitHub.
Enable Application Insights and basic operational monitoring.
Verify end-to-end production workflow:
Create Session Twin
Upload CV
Generate Mirror
Persist Twin
Retrieve Twin after login

Acceptance criteria

Production site is deployed at www.digitalcareertwin.ai.

HTTPS is enforced.

Access is restricted to approved IP addresses.

Unauthorised IPs cannot reach the application.

GitHub deployment to Azure is configured.

Production environment variables are separated from local config.

Application Insights / logging is enabled.

End-to-end DCT flow works from an approved IP.
