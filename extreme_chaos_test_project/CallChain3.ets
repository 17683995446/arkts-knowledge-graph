/**
 * 调用链文件 3
 */

import { CallChainClass4 } from './CallChain4';

export class CallChainClass3 {
    callNext() {
        const next = new CallChainClass4();
        return next.execute();
    }
    
    execute() {
        return 'CallChain3 executed';
    }
}
