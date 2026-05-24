/**
 * 调用链文件 4
 */

import { CallChainClass5 } from './CallChain5';

export class CallChainClass4 {
    callNext() {
        const next = new CallChainClass5();
        return next.execute();
    }
    
    execute() {
        return 'CallChain4 executed';
    }
}
