# Imagen base: Nginx en Alpine (liviana)
FROM nginx:alpine

# Copiar la app al directorio de Nginx
COPY index.html /usr/share/nginx/html/index.html

# Exponer el puerto 80
EXPOSE 80

# Nginx arranca automáticamente
CMD ["nginx", "-g", "daemon off;"]
