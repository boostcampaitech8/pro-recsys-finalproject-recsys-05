FROM nginx:alpine

# 기본 설정 덮어쓰기
COPY nginx.conf /etc/nginx/nginx.conf

# 포트 노출
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
