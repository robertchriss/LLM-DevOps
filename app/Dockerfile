### Stage 1: Building the TypeScript application
FROM node:14 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install --only=production
COPY . .
RUN npm run build

### Stage 2: Creating the production image
FROM node:14-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ['npm', 'start']