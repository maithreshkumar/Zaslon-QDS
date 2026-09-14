#!/bin/sh
set -eu

read_secret() {
  variable_name="$1"
  file_variable_name="${variable_name}_FILE"
  eval "current_value=\${$variable_name:-}"
  eval "secret_path=\${$file_variable_name:-}"
  if [ -z "$current_value" ] && [ -n "$secret_path" ] && [ -r "$secret_path" ]; then
    current_value="$(cat "$secret_path")"
    export "$variable_name=$current_value"
  fi
}

read_secret ZASLON_ALICE_API_KEY
read_secret ZASLON_ATTACK_API_KEY
read_secret ZASLON_BOB_API_KEY

envsubst '${API_UPSTREAM} ${ZASLON_ALICE_API_KEY} ${ZASLON_ATTACK_API_KEY} ${ZASLON_BOB_API_KEY}' \
  < /etc/zaslon/nginx.conf.template \
  > /tmp/zaslon-nginx.conf

exec nginx -c /tmp/zaslon-nginx.conf -g 'daemon off;'
