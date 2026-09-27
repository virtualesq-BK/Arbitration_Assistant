FROM node:20-alpine
WORKDIR /app
# NEXT_PUBLIC_* variables are inlined at build time.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY package.json .
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]
