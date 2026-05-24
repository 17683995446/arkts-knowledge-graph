/**
 * 调用链文件 1
 */

import { ChainClass2 } from './CallChain2';

export class ChainClass1 {
    methodA() {
        const next = new ChainClass2();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain1 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain1 C';
    }
}
