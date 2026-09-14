FROM node:22.22.0-alpine AS build

WORKDIR /src
COPY package.json package-lock.json ./
COPY Alice/package.json Alice/package.json
COPY Attack/package.json Attack/package.json
COPY Bob/package.json Bob/package.json
RUN npm ci

COPY design-system.css ./design-system.css
COPY Alice ./Alice
COPY Attack ./Attack
COPY Bob ./Bob

ENV VITE_API_URL=/api/v1
RUN npm run build

FROM nginx:1.29.1-alpine

RUN apk add --no-cache gettext
COPY --from=build /src/Alice/dist /usr/share/nginx/html/alice
COPY --from=build /src/Attack/dist /usr/share/nginx/html/attack
COPY --from=build /src/Bob/dist /usr/share/nginx/html/bob
COPY docker/nginx.conf.template /etc/zaslon/nginx.conf.template
COPY docker/frontend-entrypoint.sh /usr/local/bin/zaslon-frontend-entrypoint
RUN chmod 0555 /usr/local/bin/zaslon-frontend-entrypoint && \
    chown -R nginx:nginx /etc/zaslon /usr/share/nginx/html

USER nginx
EXPOSE 5173 5174 5175

ENTRYPOINT ["/usr/local/bin/zaslon-frontend-entrypoint"]

