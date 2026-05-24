/**
 * 调用链文件 4
 */

import { ChainClass5 } from './CallChain5';

export class ChainClass4 {
    methodA() {
        const next = new ChainClass5();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain4 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain4 C';
    }
}
