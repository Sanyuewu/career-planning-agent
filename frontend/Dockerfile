# AI 职业规划智能体 - 前端
# 阶段1: 构建
FROM node:20-alpine as builder

WORKDIR /app

# 设置 Node.js 内存限制
ENV NODE_OPTIONS="--max-old-space-size=2048"

# 先复制依赖文件，利用缓存
COPY package*.json ./

# 安装依赖
RUN npm install --legacy-peer-deps

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# 阶段2: 生产环境
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
