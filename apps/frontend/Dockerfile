FROM nginx:alpine-slim

# Copy static frontend files to Nginx web root
COPY apps/frontend/ /usr/share/nginx/html/

# Support non-root container execution
RUN touch /var/run/nginx.pid && \
    chown -R 10001:10001 /var/run/nginx.pid /usr/share/nginx/html /var/cache/nginx /var/log/nginx

USER 10001:10001

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
