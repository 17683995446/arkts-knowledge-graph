/**
 * 调用链文件 9
 */

import { ChainClass10 } from './CallChain10';

export class ChainClass9 {
    methodA() {
        const next = new ChainClass10();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain9 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain9 C';
    }
}
