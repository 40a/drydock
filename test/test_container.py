"""
Tests for `drydock.duster` module and Container object.
"""
import pytest
from drydock.duster import Container
import yaml


class TestContainer(object):
    config = """
name: blog
base: nekroze/wordpress
domain: nekroze.com
exposed_ports:
    22: 22
    2222: 222
http_port: 8081
https_port: 4431
external: No
"""

    def test_construction(self):
        container = Container(**yaml.load(self.config))
        assert container.name == "blog"
        assert container.base == "nekroze/wordpress"
        assert container.domain == "nekroze.com"
        assert container.exposed_ports == {22:22, 2222:222}
        assert container.http_port == 8081
        assert container.https_port == 4431
        assert container.external is False
        assert container.skyfqdn == "blog.wordpress.containers.drydock"
        assert container.fqdn == "blog.nekroze.com"

    def test_supervisord(self):
        container = Container(**yaml.load(self.config))
        assert container.get_supervisor_config() == """[program:blog]
command=docker start blog
autostart=true
autorestart=true"""

    def test_nginx(self):
        container = Container(**yaml.load(self.config))
        expected = """upstream blog {
    server blog.wordpress.containers.drydock;
}
server {
    listen       80;
    server_name  blog.nekroze.com;

    deny all;
    allow 192.168.1.0/24;
    allow 192.168.0.0/24;

    access_log  /var/log/nginx/log/blog.nekroze.com.access.log  main;
    error_log  /var/log/nginx/log/blog.nekroze.com.error.log;

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-NginX-Proxy true;
        proxy_redirect off;
        proxy_buffering off;

        proxy_pass https://blog:8081/;
    }
}
server {
    listen 443;
    server_name blog.nekroze.com;

    deny all;
    allow 192.168.1.0/24;
    allow 192.168.0.0/24;

    access_log  /var/log/nginx/log/blog.nekroze.com.access.log  main;
    error_log  /var/log/nginx/log/blog.nekroze.com.error.log;

    ssl on;
    ssl_session_timeout 5m;
    ssl_protocols SSLv2 SSLv3 TLSv1;
    ssl_ciphers ALL:!ADH:!EXPORT56:RC4+RSA:+HIGH:+MEDIUM:+LOW:+SSLv2:+EXP;
    ssl_prefer_server_ciphers on;
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-NginX-Proxy true;
        proxy_redirect off;
        proxy_buffering off;

        proxy_pass https://blog:4431/;
    }
}"""
        assert container.get_nginx_config() == expected

    def test_container_commands(self):
        container = Container(**yaml.load(self.config))

        assert ' '.join(container.get_docker_command()) == \
               "docker run -d -name blog -p 22:22 -p 2222:222 nekroze/wordpress"