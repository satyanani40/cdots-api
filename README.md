
FastAPI will start at http://127.0.0.1:8000

Open Swagger UI at http://127.0.0.1:8000/docs

in dev container run mongodb using below command and access in 27019
mongod --bind_ip 0.0.0.0 --dbpath /data/db --logpath /var/log/mongodb/mongod.log --fork


uvicorn runner:app --host 0.0.0.0 --port 8000 --reload
