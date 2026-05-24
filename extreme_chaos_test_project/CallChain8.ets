/**
 * 调用链文件 8
 */

import { CallChainClass9 } from './CallChain9';

export class CallChainClass8 {
    callNext() {
        const next = new CallChainClass9();
        return next.execute();
    }
    
    execute() {
        return 'CallChain8 executed';
    }
}
