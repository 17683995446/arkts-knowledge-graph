/**
 * 调用链文件 0
 */

import { ChainClass1 } from './CallChain1';

export class ChainClass0 {
    methodA() {
        const next = new ChainClass1();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain0 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain0 C';
    }
}
