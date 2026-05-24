/**
 * 调用链文件 6
 */

import { CallChainClass7 } from './CallChain7';

export class CallChainClass6 {
    callNext() {
        const next = new CallChainClass7();
        return next.execute();
    }
    
    execute() {
        return 'CallChain6 executed';
    }
}
