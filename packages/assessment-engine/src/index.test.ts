import {expect,it} from 'vitest'; import {gradeResponse,updateMastery} from './index.js';
it('grades and updates mastery',()=>{expect(gradeResponse({type:'TRUE_FALSE',correctAnswer:'true'},'true')).toBe(true); expect(updateMastery(undefined,.9).status).toBe('MASTERED');});
