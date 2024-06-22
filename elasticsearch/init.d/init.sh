#!/bin/bash
set -e

# Pre-Initialize ############################################################
psql -v ON_ERROR_STOP=1 --username postgres <<-EOSQL
	CREATE USER $DATABASE_USER PASSWORD '$POSTGRES_PASSWORD' SUPERUSER;
	CREATE ROLE repuser WITH REPLICATION LOGIN PASSWORD '$POSTGRES_PASSWORD';
	COMMIT;
EOSQL

# Initialize ################################################################

# Create Databases
psql -v ON_ERROR_STOP=1 --username postgres <<-EOSQL
	CREATE DATABASE sample OWNER $DATABASE_USER;
	COMMIT;
EOSQL

# Set Database Scheme & Data
psql -v ON_ERROR_STOP=1 --username postgres --dbname sample -f /init.d/sample.sql
