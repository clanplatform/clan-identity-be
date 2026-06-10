# Quick script to execute the already-copied SQL file
docker exec -i clan-identity-domain psql -U postgres -d auth_service -f /tmp/01_create_auth_users_table.sql
