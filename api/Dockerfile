FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY login.html /usr/share/nginx/html/login.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]