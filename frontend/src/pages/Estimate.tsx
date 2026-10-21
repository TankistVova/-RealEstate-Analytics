import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {useMutation,useQueryClient} from '@tanstack/react-query';
import {ArrowRight,Check,ScanLine} from 'lucide-react';
import {api} from '../api/client';
import type {Valuation} from '../types';
import {ApartmentFields,initialApartment,PageHead,ErrorBox} from '../components/shared';
export default function Estimate(){
 const [value,setValue]=useState(initialApartment);const navigate=useNavigate();const client=useQueryClient();
 const mutation=useMutation({mutationFn:()=>api<Valuation>('/valuations',{method:'POST',body:JSON.stringify(value)}),onSuccess:v=>{client.invalidateQueries({queryKey:['valuations']});client.invalidateQueries({queryKey:['overview']});navigate(`/valuations/${v.id}`);}});
 return <><PageHead title="Экспресс-оценка" description="Укажите характеристики квартиры — система найдёт подходящие аналоги."/><div className="estimate-layout"><form className="card" onSubmit={e=>{e.preventDefault();mutation.mutate();}}><div className="card-head"><div><h3>Характеристики квартиры</h3><p>Квартиры вторичного рынка</p></div><span className="chip">Сравнительный метод</span></div><ApartmentFields value={value} onChange={setValue}/><ErrorBox error={mutation.error}/><div className="form-footer"><span>Результат автоматически сохранится в истории</span><button className="primary" disabled={mutation.isPending}>{mutation.isPending?'Подбираем аналоги…':'Рассчитать стоимость'}<ArrowRight size={17}/></button></div></form><aside className="method-card"><ScanLine size={30}/><h3>Оценка, которую можно объяснить</h3><p>Без машинного обучения. Только сравнение характеристик и прозрачные поправки.</p>{['Подбор до 10 актуальных аналогов','Корректировки на ремонт, дом и этаж','Взвешенная цена квадратного метра','Сохранение расчёта и PDF-отчёт'].map((s,i)=><div className="method-step" key={s}><span>{i+1}</span>{s}<Check size={14}/></div>)}<small>Не менее 3 аналогов для расчёта. Если данных недостаточно, система сообщит об этом.</small></aside></div></>;
}
