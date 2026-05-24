/**
 * 调用链文件 2
 */

import { CallChainClass3 } from './CallChain3';

export class CallChainClass2 {
    callNext() {
        const next = new CallChainClass3();
        return next.execute();
    }
    
    execute() {
        return 'CallChain2 executed';
    }
}
