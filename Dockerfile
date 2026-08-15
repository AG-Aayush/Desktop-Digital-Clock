# nginx is a battle-tested web server. The alpine variant is ~40MB
# instead of ~190MB -- for serving static files we need nothing more.
FROM nginx:1.27-alpine

# Our own config replaces the default. Copied before the site content
# because it changes far less often, so edits to the page reuse this
# cached layer instead of rebuilding it.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# The site itself.
COPY docs/ /usr/share/nginx/html/

# Documents intent. It does not publish the port by itself -- that is
# what -p does at run time.
EXPOSE 80

# Tell Docker how to know the container is not just running, but working.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1
