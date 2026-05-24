/**
 * 调用链文件 1
 */

import { CallChainClass2 } from './CallChain2';

export class CallChainClass1 {
    callNext() {
        const next = new CallChainClass2();
        return next.execute();
    }
    
    execute() {
        return 'CallChain1 executed';
    }
}
