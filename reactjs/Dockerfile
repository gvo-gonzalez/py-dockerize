# pull official base image
FROM node:14.1-alpine as builder

# set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
COPY package*.json ./
#COPY package-lock.json ./
# Fix error core-js@<3 is no longer maintained: npm install -g npm
RUN npm install -g npm
RUN npm install --silent
#RUN npm install react-scripts@3.4.1 -g --silent
RUN npm audit fix

# add app
COPY . ./
#EXPOSE 3000
# start app
#CMD ["npm", "start"]
RUN npm run build

FROM nginx:1.16.0-alpine
COPY --from=builder /app/build /usr/share/nginx/html
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/react-nginx.conf /etc/nginx/conf.d
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]