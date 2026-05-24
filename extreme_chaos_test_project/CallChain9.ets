/**
 * 调用链文件 9
 */

import { CallChainClass0 } from './CallChain0';

export class CallChainClass9 {
    callNext() {
        const next = new CallChainClass0();
        return next.execute();
    }
    
    execute() {
        return 'CallChain9 executed';
    }
}
