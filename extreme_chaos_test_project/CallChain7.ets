/**
 * 调用链文件 7
 */

import { CallChainClass8 } from './CallChain8';

export class CallChainClass7 {
    callNext() {
        const next = new CallChainClass8();
        return next.execute();
    }
    
    execute() {
        return 'CallChain7 executed';
    }
}
