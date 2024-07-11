#!/bin/sh


MASTER_USERNAME=$1
MASTER_PASSWORD=$2

DOMAIN=$3
REALM=$4
ADMIN_USERNAME=$5
ADMIN_PASSWORD=$6

set -e

# get session
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --client admin-cli --user $MASTER_USERNAME --password $MASTER_PASSWORD &>/dev/null

# create realm
echo -n "create realm ($REALM) "
/opt/keycloak/bin/kcadm.sh create realms -s realm=$REALM -s enabled=true &>/dev/null
echo "[ OK ]"

# create groups
echo -n "create group (Users) "
GROUP_USER_UUID=$(/opt/keycloak/bin/kcadm.sh create -r $REALM groups -b '{"name":"Users","attributes":{"policy":["user"]}}' -i)
echo "[ OK ]"
echo -n "create group (Administrators) "
GROUP_ADMIN_UUID=$(/opt/keycloak/bin/kcadm.sh create -r $REALM groups -b '{"name":"Administrators","attributes":{"policy":["admin"]}}' -i)
echo "[ OK ]"

# create user
echo -n "create user ($ADMIN_USERNAME) "
USER_UUID=$(/opt/keycloak/bin/kcadm.sh create -r $REALM users -b "{\"username\":\"$ADMIN_USERNAME\",\"firstName\":\"$ADMIN_USERNAME\",\"lastName\":\"$ADMIN_USERNAME\",\"email\":\"$ADMIN_USERNAME@$DOMAIN\",\"enabled\":true,\"requiredActions\":[\"UPDATE_PASSWORD\"]}" -i)
echo "[ OK ]"

# set temporary password
echo -n "set user ($ADMIN_USERNAME) password ($ADMIN_PASSWORD) "
/opt/keycloak/bin/kcadm.sh set-password -r $REALM --username $ADMIN_USERNAME --new-password "$ADMIN_PASSWORD" --temporary
echo "[ OK ]"

# set groups
echo -n "join user ($ADMIN_USERNAME) to group (Users And Administrators) "
/opt/keycloak/bin/kcadm.sh update -r $REALM users/$USER_UUID/groups/$GROUP_USER_UUID
/opt/keycloak/bin/kcadm.sh update -r $REALM users/$USER_UUID/groups/$GROUP_ADMIN_UUID
echo "[ OK ]"

# set minio openid
## create client scope
echo -n "create client scope (eqpls-client-scope) "
SCOPE_UUID=$(/opt/keycloak/bin/kcadm.sh create -r $REALM client-scopes -b "{\"name\":\"eqpls-client-scope\",\"description\":\"eqpls-client-scope\",\"type\":\"none\",\"protocol\":\"openid-connect\",\"attributes\":{\"display.on.consent.screen\":\"true\",\"consent.screen.text\":\"\",\"include.in.token.scope\":\"true\",\"gui.order\":\"\"}}" -i)
echo "[ OK ]"

## set policy mapper
echo -n "set policy mapper (policy) "
/opt/keycloak/bin/kcadm.sh create -r $REALM client-scopes/$SCOPE_UUID/protocol-mappers/models -b "{\"protocol\":\"openid-connect\",\"protocolMapper\":\"oidc-usermodel-attribute-mapper\",\"name\":\"policy\",\"config\":{\"claim.name\":\"policy\",\"jsonType.label\":\"String\",\"id.token.claim\":\"true\",\"access.token.claim\":\"true\",\"lightweight.claim\":\"false\",\"userinfo.token.claim\":\"true\",\"introspection.token.claim\":\"true\",\"multivalued\":\"true\",\"aggregate.attrs\":\"true\",\"user.attribute\":\"policy\"}}" &>/dev/null
echo "[ OK ]"

## create client
echo -n "create client (eqpls) "
CLIENT_UUID=$(/opt/keycloak/bin/kcadm.sh create -r $REALM clients -b "{\"protocol\":\"openid-connect\",\"clientId\":\"eqpls\",\"name\":\"eqpls\",\"description\":\"eqpls\",\"publicClient\":false,\"authorizationServicesEnabled\":false,\"serviceAccountsEnabled\":false,\"implicitFlowEnabled\":false,\"directAccessGrantsEnabled\":true,\"standardFlowEnabled\":true,\"frontchannelLogout\":true,\"attributes\":{\"saml_idp_initiated_sso_url_name\":\"\",\"oauth2.device.authorization.grant.enabled\":false,\"oidc.ciba.grant.enabled\":false},\"alwaysDisplayInConsole\":true,\"rootUrl\":\"https://$DOMAIN\",\"baseUrl\":\"https://$DOMAIN\",\"redirectUris\":[\"*\"]}" -i)
echo "[ OK ]"

## set client option
echo -n "set client options to (eqpls) "
/opt/keycloak/bin/kcadm.sh update -r $REALM clients/$CLIENT_UUID -s 'attributes."access.token.lifespan"="3600"' -s 'attributes."use.jwks.url"="true"' -s 'attributes."use.refresh.tokens"="true"' -s 'attributes."client.use.lightweight.access.token.enabled"="false"' -s 'attributes."client_credentials.use_refresh_token"="false"' -s 'attributes."acr.loa.map"="{}"' -s 'attributes."require.pushed.authorization.requests"="false"' -s 'attributes."tls.client.certificate.bound.access.tokens"="false"' -s 'attributes."display.on.consent.screen"="false"' -s 'attributes."token.response.type.bearer.lower-case"="false"'
echo "[ OK ]"

## set default client
echo -n "set default client scope (eqpls-client-scope) to client (eqpls) "
/opt/keycloak/bin/kcadm.sh update -r $REALM clients/$CLIENT_UUID/default-client-scopes/$SCOPE_UUID -b '{}'
echo "[ OK ]"
