#!/bin/bash

helpFunction()
{
   echo ""
   echo "Usage: $0 -p populate"
   echo -e "\t-p: Populate the database or not (true|false)"
   exit 1
}

while getopts "p:" OPTION
do
     case $OPTION in
         p)
             POPULATE=$OPTARG
             ;;
         ?)
             helpFunction
             exit
             ;;
     esac
done

if [[ -z $POPULATE ]]; then
  echo "[ERROR] Populated parameter CANNOT be empty!"
  helpFunction
else
  if [[ $POPULATE != "true" ]] && [[ $POPULATE != "false" ]]; then
    echo "[ERROR] Wrong parameter value"
    helpFunction
  else
    cd src/
    echo "[INFO] Initialize database"
    flask init-db
    if [[ "$POPULATE" = "true" ]]; then
      echo "[INFO] Populating database"
      flask populate-db
    else
      echo "[INFO] Database is NOT populated"
    fi
  fi
fi

flask run

