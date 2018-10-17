ARG CIRCLE_BRANCH
FROM unnotechpromotion/grizzly:$CIRCLE_BRANCH as project

# using multi-staging with multiple copies to continuously keep the environment and avoid the maximum image layer error
FROM python:3.6.5
WORKDIR /usr/src/app
EXPOSE 8000

# Install vim, enable compilemessages and m2crypto
RUN apt-get update &&     apt-get install vim -y

# To copy existing python packages commands
COPY --from=project /usr/local/bin/. /usr/local/bin/.

# To copy existing python packages
COPY --from=project /usr/local/lib/python3.6/site-packages/. /usr/local/lib/python3.6/site-packages/.

# COPY locale locale
# RUN python manage.py compilemessages
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# To copy existing migration files
COPY --from=project /usr/src/app/. .

COPY . .
RUN timeout 30 yes | python manage.py makemigrations

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
