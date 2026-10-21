const base = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
export async function api<T>(path:string, options:RequestInit={}):Promise<T> {
  const headers=new Headers(options.headers);
  const token=sessionStorage.getItem('token');
  if(token) headers.set('Authorization',`Bearer ${token}`);
  if(options.body && !(options.body instanceof FormData)) headers.set('Content-Type','application/json');
  const response=await fetch(base+path,{...options,headers});
  if(!response.ok){
    if(response.status===401 && !path.startsWith('/auth/')) {sessionStorage.removeItem('token'); window.dispatchEvent(new Event('auth-expired'));}
    const body=await response.json().catch(()=>({detail:'Сервер недоступен'}));
    const detail=Array.isArray(body.detail)?body.detail.map((e:{loc:string[];msg:string})=>`${e.loc.slice(1).join('.')}: ${e.msg}`).join('; '):body.detail;
    throw new Error(detail||'Ошибка запроса');
  }
  if(path.endsWith('/report')) return await response.blob() as T;
  return response.status===204?undefined as T:await response.json();
}
export async function downloadReport(id:number){const blob=await api<Blob>(`/valuations/${id}/report`); const url=URL.createObjectURL(blob); const a=document.createElement('a');a.href=url;a.download=`valuation-${id}.pdf`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
