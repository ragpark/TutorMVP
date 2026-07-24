export const API=process.env.NEXT_PUBLIC_API_URL??'http://localhost:4000';
export const learnerId='demo-learner-id';
export async function getJson(path:string){try{const r=await fetch(`${API}${path}`,{cache:'no-store'}); return r.ok?await r.json():null;}catch{return null;}}
