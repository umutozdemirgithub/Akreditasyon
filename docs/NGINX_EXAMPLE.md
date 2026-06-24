# Örnek Nginx Reverse Proxy

Aşağıdaki örnek, `docker-compose.web.yml` ile çalışan web servisinin önüne kurum alan adı ve TLS koymak içindir.

```nginx
server {
    listen 80;
    server_name medek.example.edu.tr;
    return 301 https://$host$request_uri;
}

limit_req_zone $binary_remote_addr zone=medek_general:10m rate=120r/m;
limit_req_zone $binary_remote_addr zone=medek_login:10m rate=10r/m;

server {
    listen 443 ssl http2;
    server_name medek.example.edu.tr;

    ssl_certificate     /etc/letsencrypt/live/medek.example.edu.tr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/medek.example.edu.tr/privkey.pem;

    client_max_body_size 100m;

    location /api/auth/login {
        limit_req zone=medek_login burst=10 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        limit_req zone=medek_general burst=60 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Kurumsal ağda IP allowlist, VPN veya kurum kimlik doğrulama katmanı önerilir.
