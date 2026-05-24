/**
 * 调用链文件 11
 */

import { ChainClass0 } from './CallChain0';

export class ChainClass11 {
    methodA() {
        const next = new ChainClass0();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain11 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain11 C';
    }
}
