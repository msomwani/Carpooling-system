FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm install

# Copy everything else
COPY . .

EXPOSE 3000

# Set environment to development for next.js hot reloading
ENV NODE_ENV=development

# Start the dev server
CMD ["npm", "run", "dev"]
