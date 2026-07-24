import {expect,it} from 'vitest'; import {recommendNextAction} from './index.js';
it('recommends diagnostic first',()=>{expect(recommendNextAction({learnerId:'l',objectives:[],masteries:[],prerequisites:{},assessmentAttemptCount:0}).actionType).toBe('TAKE_DIAGNOSTIC');});
