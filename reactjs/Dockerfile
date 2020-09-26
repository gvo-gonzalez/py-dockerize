# pull official base image
FROM node:14.2.0 as builder

# set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
COPY package*.json ./
RUN npm install
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
EXPOSE 3080
CMD ["nginx", "-g", "daemon off;"]