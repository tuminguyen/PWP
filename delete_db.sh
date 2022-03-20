#!/bin/bash

# delete all the tables and database

cd src/
flask delete-db
cd ../
rm -rf db/byc.db