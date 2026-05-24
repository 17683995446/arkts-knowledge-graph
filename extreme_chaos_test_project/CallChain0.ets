/**
 * 调用链文件 0
 */

import { CallChainClass1 } from './CallChain1';

export class CallChainClass0 {
    callNext() {
        const next = new CallChainClass1();
        return next.execute();
    }
    
    execute() {
        return 'CallChain0 executed';
    }
}
