#!/usr/bin/env sh

yes YES | gcloud app deploy app.yml

if [ $? = 0 ] || [ $? = 141 ]
then
    echo "Experienced exit code $?: Successful! "
    exit 0
else
    echo "Experienced exit code $?: Failed!"
    false
fi