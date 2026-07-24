import {Queue, Worker} from 'bullmq';
export const jobNames=['GENERATE_RECOMMENDATION','RECALCULATE_MASTERY','SUMMARIZE_TUTOR_SESSION'] as const;
const redisUrl=process.env.REDIS_URL;
export async function runSyncFallback(name:string,payload:unknown){ return {name,payload,status:'completed-synchronously',note:'Redis unavailable; deterministic MVP fallback used.'}; }
if(redisUrl){ const connection={url:redisUrl}; new Queue('adaptive-tutor', {connection}); new Worker('adaptive-tutor', async job=>({status:'completed',job:job.name}), {connection}); console.log('Worker listening for adaptive-tutor jobs'); } else { console.log('REDIS_URL not set; worker documents synchronous fallback for local development.'); }
