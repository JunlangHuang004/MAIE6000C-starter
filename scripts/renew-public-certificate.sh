#!/bin/sh
set -eu
cd /opt/nutrichat
docker run --rm \
  -v /opt/nutrichat/deploy/public/letsencrypt:/etc/letsencrypt \
  -v /opt/nutrichat/deploy/public/acme:/var/www/acme \
  certbot/certbot:v5.4.0 renew --quiet
docker compose -f compose.cloud.yaml -f compose.public.yaml exec -T proxy nginx -t
docker compose -f compose.cloud.yaml -f compose.public.yaml exec -T proxy nginx -s reload
