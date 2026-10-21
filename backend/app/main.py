from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app=FastAPI(title='RealEstate Analytics',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_credentials=False,allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Authorization','Content-Type'])
app.include_router(router)

@app.get('/health')
def health(): return {'status':'ok'}
