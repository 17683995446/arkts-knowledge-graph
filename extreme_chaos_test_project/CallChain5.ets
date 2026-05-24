/**
 * 调用链文件 5
 */

import { CallChainClass6 } from './CallChain6';

export class CallChainClass5 {
    callNext() {
        const next = new CallChainClass6();
        return next.execute();
    }
    
    execute() {
        return 'CallChain5 executed';
    }
}
