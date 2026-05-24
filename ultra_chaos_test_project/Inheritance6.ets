/**
 * 继承层次结构 - 中间层 6
 */

import { BaseClass5 } from './Inheritance5';

export abstract class BaseClass6 extends BaseClass5 {
    intermediateMethod(): void {
        console.log('intermediate method 6');
    }
}
